# Phase 1: Hello Coding Agent — Khung sườn với AgentSeek

> **Mục tiêu**: Xây dựng phiên bản Coding Agent đầu tiên có khả năng giao tiếp, hiểu vai trò lập trình viên, gọi custom tool phân tích mã nguồn và theo dõi vết suy luận qua LangSmith.
>
> **Thời gian ước tính**: 1.5 - 2 giờ
>
> **AgentSeek template tham khảo**: `deepagents/default`
>
> **Prerequisites**: Đã cài đặt Python 3.12+, `uv`, và có API key từ một trong các provider (SiliconFlow, OpenAI, Anthropic, Google).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Kiến trúc 3 tầng của một AI Agent
Trong hệ sinh thái phát triển Agent hiện đại (đặc biệt là hệ sinh thái LangChain / LangGraph), một hệ thống Coding Agent bền bỉ được xây dựng trên 3 tầng phân tách rõ ràng:

1. **Tầng Runtime (LangGraph)**:
   - Đóng vai trò là "động cơ thực thi" (Execution Engine).
   - Quản lý trạng thái (State Persistence), hỗ trợ checkpointing, vòng lặp điều kiện (Cyclic Graphs), và cơ chế dừng lại để tương tác với con người (Human-in-the-Loop).
   - Đảm bảo agent có thể chạy trong thời gian dài (durable execution) mà không bị mất dấu vết trạng thái khi gặp sự cố mạng hoặc tiến trình bị ngắt.

2. **Tầng Framework (LangChain)**:
   - Cung cấp các lớp trừu tượng hóa cho Mô hình ngôn ngữ lớn (LLM Abstractions như `ChatOpenAI`, `ChatAnthropic`).
   - Cung cấp chuẩn hóa về Tools (`@tool`), Messages (`HumanMessage`, `AIMessage`, `ToolMessage`), và xử lý định dạng có cấu trúc (Structured Outputs).

3. **Tầng Harness (Deep Agents)**:
   - Là bộ khung điều khiển (Harness) được xây dựng sẵn trên LangGraph và LangChain, được thiết kế chuyên biệt cho các tác vụ giải quyết vấn đề phức tạp, kéo dài nhiều bước (long-horizon tasks).
   - Tích hợp sẵn Virtual File System (VFS), Todo List / Task Planning Middleware, Context Compression, và Sub-agent delegation.
   - Thay vì phải tự ghép từng node và edge trong LangGraph, Deep Agents cung cấp hàm `create_deep_agent()` gói sẵn kiến trúc tối ưu.

```
┌────────────────────────────────────────────────────────┐
│               Agent Harness (Deep Agents)              │
│   Virtual File System | TodoList | Memory | Subagents  │
├────────────────────────────────────────────────────────┤
│               Framework Layer (LangChain)              │
│       Model Abstractions | Tool Interfaces | Prompts   │
├────────────────────────────────────────────────────────┤
│               Runtime Engine (LangGraph)               │
│       State Graph | Checkpointing | Event Streaming    │
└────────────────────────────────────────────────────────┘
```

### 1.2 Context Engineering cho Coding Agent
Một sai lầm phổ biến khi bắt đầu xây dựng coding agent là **Prompt Stuffing** (nhồi nhét toàn bộ source code vào system prompt). Cách làm này nhanh chóng làm cạn kiệt context window, tăng chi phí token, và làm LLM bị "mất tập trung" (Lost in the Middle).

**Context Engineering** là triết lý cốt lõi của Deep Agents:
- Coi Context Window của mô hình là một nguồn tài nguyên quý giá, giới hạn.
- Cung cấp cho Agent các công cụ (Tools) để Agent **tự chủ động kéo thông tin vào khi cần** và **đẩy thông tin ra ngoài (offload) khi không còn dùng đến**.
- Trong Phase 1, bạn sẽ thấy cách Agent chỉ nhận prompt ngắn gọn định hình vai trò và dùng Tool để phân tích code khi người dùng yêu cầu, thay vì đọc sẵn toàn bộ code ngay từ đầu.

### 1.3 Vòng đời phát triển với AgentSeek
AgentSeek là bộ công cụ quản lý vòng đời ứng dụng AI (Application Development Lifecycle - ADLC). Nó chuẩn hóa quy trình làm việc thông qua các lệnh nhất quán:
- `agentseek create <template>`: Khởi tạo dự án chuẩn hóa từ kho template.
- `agentseek info`: Xem siêu dữ liệu, entry point và cấu hình của dự án.
- `agentseek task sync`: Cài đặt dependencies (backend Python qua `uv`, frontend qua `npm`).
- `agentseek doctor`: Kiểm tra tính toàn vẹn của môi trường, file cấu hình và biến môi trường.
- `agentseek dev`: Khởi chạy môi trường phát triển local.

---

## 2. Tài liệu tham khảo mở rộng

Trước khi bắt tay vào code hoặc khi muốn đào sâu hơn, bạn nên tham khảo các tài liệu sau trong thư mục `guideline/`:

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [00_preparation.md](../guideline/00_preparation.md) | Mục 1 đến Mục 8 | Nắm vững cách AgentSeek quản lý cấu hình `.env` đa nhà cung cấp và cài đặt `uv`. |
| [03_agent_framework_to_agent_harness.md](../guideline/03_agent_framework_to_agent_harness.md) | Bảng so sánh 3 tầng & Context Engineering | Hiểu sâu sự khác biệt giữa Framework thuần túy và Agent Harness. |
| [04_quickstart_first_deep_agent.md](../guideline/04_quickstart_first_deep_agent.md) | Hello World & Viết Custom Tool | Xem cú pháp chuẩn của hàm `create_deep_agent` và quy tắc 3 yếu tố của Tool. |
| [01_deepagent_version_update.md](../guideline/01_deepagent_version_update.md) | Thay đổi ở phiên bản v0.7+ | Hiểu lý do tại sao Base Prompt mặc định rỗng và bạn phải tự viết System Prompt rõ ràng. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Khởi tạo dự án từ template AgentSeek

Mở terminal và sử dụng AgentSeek để tạo khung sườn dự án:

```bash
# Liệt kê các template có sẵn trên nhánh main
agentseek create --list-templates --checkout main

# Khởi tạo dự án coding-agent dựa trên template deepagents/default
agentseek create deepagents/default --checkout main --no-input

# Di chuyển vào thư mục dự án vừa sinh ra
cd deepagents_default
```

Sau khi tạo, kiểm tra cấu trúc dự án:
```bash
agentseek info
agentseek task sync
agentseek doctor
```

### Bước 2: Cấu hình biến môi trường (`.env`)

Tạo file `.env` từ file mẫu `.env.example`. Điền thông tin Model Provider và cấu hình LangSmith:

```bash
cp .env.example .env
```

Nội dung cấu hình trong file `.env`:

```ini
# Lựa chọn 1: Dùng SiliconFlow (Khuyến nghị cho khóa học, OpenAI-compatible)
AGENTSEEK_MODEL_PROVIDER=openai
AGENTSEEK_MODEL=zai-org/GLM-5.2
OPENAI_API_BASE=https://api.siliconflow.cn/v1
OPENAI_API_KEY=sk-your-siliconflow-api-key

# Lựa chọn 2: Nếu bạn dùng OpenAI trực tiếp
# AGENTSEEK_MODEL_PROVIDER=openai
# AGENTSEEK_MODEL=gpt-4.1-mini
# OPENAI_API_KEY=sk-your-openai-key

# Lựa chọn 3: Nếu bạn dùng Anthropic
# AGENTSEEK_MODEL_PROVIDER=anthropic
# AGENTSEEK_MODEL=claude-3-5-sonnet-20241022
# ANTHROPIC_API_KEY=sk-ant-your-key

# Cấu hình LangSmith Tracing (Rất quan trọng để quan sát Agent)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_langsmith_key
LANGSMITH_PROJECT=coding-agent-phase1
```

### Bước 3: Định nghĩa Custom Tool — Phân tích cú pháp code

Trong Deep Agents, một tool đạt chuẩn phải thỏa mãn **3 yếu tố**:
1. **Type Annotations**: Khai báo kiểu dữ liệu tường minh cho tất cả tham số và giá trị trả về.
2. **Docstring chuẩn Google/Sphinx**: Mô tả rõ mục đích của tool và từng tham số.
3. **Default Values**: Cung cấp giá trị mặc định cho các tham số tùy chọn.

Tạo file `src/tools/code_analyzer.py`:

```python
"""Custom tool phân tích cấu trúc mã nguồn Python cơ bản."""

import ast
from langchain_core.tools import tool


@tool
def analyze_python_code(code_snippet: str) -> str:
    """Phân tích cú pháp một đoạn mã nguồn Python và trích xuất danh sách hàm, class cùng các lỗi cú pháp (SyntaxError).

    Args:
        code_snippet: Chuỗi chứa mã nguồn Python cần phân tích.

    Returns:
        Bản tóm tắt cấu trúc gồm danh sách các hàm, class hoặc thông báo lỗi cú pháp.
    """
    try:
        tree = ast.parse(code_snippet)
    except SyntaxError as e:
        return f"Lỗi cú pháp (SyntaxError): {e.msg} tại dòng {e.lineno}, cột {e.offset}."

    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    async_functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]

    summary = []
    summary.append(f"- Tổng số Class: {len(classes)} ({', '.join(classes) if classes else 'Không có'})")
    summary.append(f"- Tổng số Function: {len(functions)} ({', '.join(functions) if functions else 'Không có'})")
    if async_functions:
        summary.append(f"- Async Functions: {len(async_functions)} ({', '.join(async_functions)})")

    return "\n".join(summary)
```

### Bước 4: Viết System Prompt định hình Coding Persona

Từ phiên bản `deepagents` v0.7+, framework đã loại bỏ các prompt mặc định cồng kềnh để tiết kiệm token (~65% base tokens). Do đó, bạn cần tự định nghĩa System Prompt định hình rõ:
- Agent là ai?
- Nguyên tắc làm việc khi đọc/sửa code là gì?
- Khi nào nên dùng tool?

Tạo file `src/prompts.py`:

```python
"""System prompts cho Coding Agent."""

CODING_AGENT_SYSTEM_PROMPT = """Bạn là một Senior Python Software Engineer và AI Coding Assistant chuyên nghiệp.

Nguyên tắc làm việc của bạn:
1. Độc lập và cẩn trọng: Khi được cung cấp mã nguồn, hãy ưu tiên dùng công cụ `analyze_python_code` để kiểm tra tính hợp lệ về cú pháp và cấu trúc trước khi đưa ra nhận xét.
2. Trả lời súc tích: Giải thích ngắn gọn nguyên nhân gây lỗi và đề xuất giải pháp tối ưu kèm ví dụ cụ thể.
3. Không phỏng đoán: Nếu thiếu ngữ cảnh hoặc mã nguồn không đầy đủ, hãy đặt câu hỏi làm rõ thay vì giả định sai lệch.
"""
```

### Bước 5: Lắp ráp Agent với `create_deep_agent`

Tạo file `src/agent.py`:

```python
"""Khởi tạo và cấu hình Deep Agent."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

from src.tools.code_analyzer import analyze_python_code
from src.prompts import CODING_AGENT_SYSTEM_PROMPT

# Nạp biến môi trường từ .env
load_dotenv()


def build_coding_agent():
    """Khởi tạo mô hình và đóng gói thành Deep Agent."""
    # Khởi tạo mô hình từ cấu hình môi trường
    model_name = os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,  # Nhiệt độ thấp giúp code ổn định, chính xác
    )

    # Danh sách công cụ cấp cho Agent trong Phase 1
    tools = [analyze_python_code]

    # Khởi tạo Deep Agent harness
    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=CODING_AGENT_SYSTEM_PROMPT,
    )

    return agent


if __name__ == "__main__":
    # Test thử agent
    bot = build_coding_agent()
    sample_code = """
def calculate_area(radius):
    pi = 3.14159
    return pi * (radius ** 2)

class CircleGeometry:
    def __init__(self, r):
        self.r = r
"""
    user_query = f"Hãy phân tích cấu trúc đoạn code sau và cho tôi biết có hàm nào:\n```python\n{sample_code}\n```"
    
    response = bot.invoke({"messages": [{"role": "user", "content": user_query}]})
    
    # In tin nhắn cuối cùng từ Agent
    last_message = response["messages"][-1]
    print("\n--- PHẢN HỒI TỪ AGENT ---")
    print(last_message.content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Hãy thử chạy một kịch bản gỡ lỗi cú pháp thực tế:

```bash
python -m src.agent
```

**Đoạn code kiểm tra phát hiện lỗi cú pháp:**
Nếu bạn truyền vào đoạn code bị lỗi (ví dụ thiếu dấu hai chấm `:` ở khai báo hàm):
```python
def broken_syntax(x, y)
    return x + y
```

**Luồng suy luận của Agent**:
1. Agent nhận yêu cầu từ người dùng.
2. Nhờ System Prompt định hướng, Agent quyết định gọi tool `analyze_python_code(code_snippet=...)`.
3. Tool chạy `ast.parse()` gặp lỗi `SyntaxError: expected ':'` và trả về thông báo lỗi chi tiết dòng, cột.
4. Agent tiếp nhận output từ tool và trả lời người dùng: chỉ ra chính xác vị trí thiếu dấu hai chấm và cung cấp đoạn code đã sửa đúng.

---

## 5. Checkpoint — Tự kiểm tra

Sau khi hoàn thành Phase 1, bạn tự xác nhận các tiêu chí sau:

- [ ] Lệnh `agentseek doctor` trả về toàn bộ trạng thái xanh (Passed/OK).
- [ ] Script `python -m src.agent` chạy thành công mà không gặp lỗi kết nối API.
- [ ] Terminal hiển thị rõ phản hồi của Agent phân tích được class và function từ đoạn code mẫu.
- [ ] Đăng nhập vào [LangSmith Dashboard](https://smith.langchain.com/), mở project `coding-agent-phase1`:
  - Bạn thấy một trace mới xuất hiện.
  - Trace ghi lại rõ: User Input -> LLM Tool Call `analyze_python_code` -> Tool Execution Result -> Final LLM Response.

---

## 6. Lỗi thường gặp & Best Practices

1. **Lỗi `ValidationError` khi gọi Tool**:
   - *Nguyên nhân*: Hàm Python của tool thiếu type annotation cho tham số hoặc kiểu trả về.
   - *Khắc phục*: Luôn viết `def my_tool(param: str) -> str:`.

2. **Lỗi 401 Unauthorized từ Model Provider**:
   - *Nguyên nhân*: `OPENAI_API_KEY` trong file `.env` chưa chính xác hoặc quên gọi `load_dotenv()`.
   - *Khắc phục*: Kiểm tra lại key với lệnh `echo $OPENAI_API_KEY` hoặc in `os.getenv("OPENAI_API_KEY")`.

3. **System Prompt quá dài làm tốn token**:
   - *Khắc phục*: Trong v0.7+, hãy giữ system prompt cô đọng dưới 300 từ, tập trung vào phong cách lập trình và các quy tắc tool bắt buộc.
