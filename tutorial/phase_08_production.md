# Phase 8: Production Polish — Streaming, Memory, MCP, và H2/2026 Stack

> **Mục tiêu**: Hoàn thiện toàn diện sản phẩm Coding Agent đưa vào môi trường Production: Streaming sự kiện thời gian thực (v3 GA Typed Projections), Trí nhớ dài hạn cá nhân hóa theo từng developer (v0.8 Personalized Memory), Tích hợp Model Context Protocol (MCP), Đóng gói Skills tái sử dụng, và tận dụng hệ sinh thái mới nhất H2/2026 (Managed Deep Agents, LLM Gateway, Context Hub).
>
> **Thời gian ước tính**: 3 - 4 giờ
>
> **AgentSeek templates tham khảo**: `deepagents/streaming`, `deepagents/mcp`, `deepagents/powercontext`
>
> **Prerequisites**: Hoàn thành [Phase 7: Quality Gate](phase_07_quality_gate.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Event Streaming v3 (Generally Available H2/2026)
Trong các ứng dụng giao diện người dùng (React, Web CLI, CopilotKit), người dùng không thể chờ đợi 30-60 giây trong im lặng để Agent hoàn thành một chuỗi suy luận phức tạp. Họ cần thấy:
- Token văn bản xuất hiện dạng gõ phím (typing effect).
- Thông báo thời gian thực khi Agent gọi công cụ (`Calling: grep...`).
- Trạng thái vòng đời khi Sub-agent được sinh ra và chạy ngầm.

Giao thức **Streaming v3 GA** mang đến khái niệm **Typed Projections** (Các phép chiếu có kiểu dữ liệu):
- Thay vì phải tự bóc tách chuỗi sự kiện thô (raw events dictionary) phức tạp từ đồ thị LangGraph, bạn có thể lắng nghe trực tiếp vào các stream chuyên biệt:
  - `stream.messages`: Token văn bản từ mô hình.
  - `stream.tool_calls`: Sự kiện bắt đầu và kết thúc của từng tool call.
  - `stream.subagents`: Vòng đời khởi tạo, đường dẫn duy nhất (`path`) và trạng thái hoàn thành của từng sub-agent.
  - `stream.output`: Trạng thái cuối cùng của toàn bộ phiên chạy.
- **Hàm `interleave()`**: Tự động đồng bộ hóa thứ tự thời gian giữa việc stream văn bản và việc thực thi công cụ.

### 1.2 Trí nhớ dài hạn (Long-term Memory) & Kiến trúc v0.8 (24/09/2026)
1. **Bản chất của Memory trong Deep Agents**:
   - Khác với context window tạm thời, Long-term Memory được lưu trữ trong `StoreBackend` (hoặc `SeekDB` trong hệ sinh thái AgentSeek).
   - Tự động trích xuất các thông tin sở thích, convention code của lập trình viên và nạp lại vào phiên làm việc sau.
2. **Cập nhật đột phá v0.8: Personalized Memory Layer**:
   - *Trước v0.8*: Toàn bộ Agent chia sẻ một kho bộ nhớ chung. Nếu Developer A thích code thụt lề 2 spaces, còn Developer B thích 4 spaces, Agent sẽ bị "rối loạn đa nhân cách".
   - *Từ v0.8*: Memory được gắn liền với **Authenticated Caller (ID của người gọi)**:
     - Khi chat 1-1: Agent sử dụng **Personal Memory** riêng biệt cho từng developer.
     - Khi trong kênh nhóm hoặc webhook: Agent chuyển sang dùng **Shared Memory** chung của cả team.
3. **Phân biệt Memory vs Credentials**:
   - `Memory`: Agent nhớ gì về thói quen code của bạn.
   - `Credentials`: Agent dùng tài khoản nào của bạn khi thao tác với GitHub, Jira, AWS.

### 1.3 Model Context Protocol (MCP)
**MCP** là chuẩn mở do Anthropic khởi xướng và được LangChain tích hợp sâu rộng trong H2/2026:
- Thay vì mỗi công cụ phải tự viết adapter riêng, một MCP Server (ví dụ: GitHub MCP, Postgres MCP, Filesystem MCP) có thể kết nối với bất kỳ Agent nào.
- 3 nguyên thủy cốt lõi của MCP:
  - **Tools**: Các hàm thực thi có thể gọi (tương tự `@tool`).
  - **Resources**: Dữ liệu ngữ cảnh dạng file/schema đọc được.
  - **Prompts**: Các mẫu prompt tái sử dụng được server cung cấp.
- `MultiServerMCPClient`: Cho phép một Deep Agent kết nối đồng thời với nhiều MCP server qua transport `stdio` hoặc `Streamable HTTP`.
- **Yêu cầu bất đồng bộ (Async-only)**: Toàn bộ tương tác MCP trong LangChain bắt buộc chạy qua giao diện `ainvoke` / `astream`.

### 1.4 Hệ sinh thái H2/2026: Managed Deep Agents & LLM Gateway
Khi triển khai cho doanh nghiệp, bạn có thể tận dụng các dịch vụ mới nhất từ LangChain / LangSmith:
1. **Managed Deep Agents (Public Beta 08/2026)**:
   - Hosted runtime trên nền tảng LangSmith. Không cần tự dựng server backend, chỉ cần chạy lệnh `mda deploy` từ CLI.
   - Hỗ trợ sẵn Durable Execution, tự động Checkpoint, Sandbox MicroVM và giao diện Human-in-the-Loop trên Cloud.
2. **LangSmith LLM Gateway (Public Beta 08/2026)**:
   - Đóng vai trò là lớp proxy trung gian giữa Agent và các nhà cung cấp mô hình.
   - Tự động **Model Fallback**: Nếu SiliconFlow hoặc OpenAI bị rate limit -> tự động chuyển tiếp sang Anthropic mà không làm gián đoạn Agent.
   - Tự động quét và che giấu thông tin nhạy cảm (PII & Secret Redaction) trước khi gửi ra ngoài internet.
3. **LangSmith Context Hub**:
   - Nền tảng quản lý version-control cho System Prompts, Skills và Policies, tách biệt khỏi mã nguồn ứng dụng để Tech Lead và Product Manager có thể cập nhật hành vi Agent mà không cần redeploy code.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [16_streaming.md](../guideline/16_streaming.md) | V3 Typed Projections & Interleave | Cách tiêu thụ stream sự kiện thời gian thực cho frontend. |
| [10_long_term_memory.md](../guideline/10_long_term_memory.md) | MemoryMiddleware & StoreBackend | Cơ chế lưu trữ tri thức dài hạn cross-session và phân chia namespace. |
| [14_mcp.md](../guideline/14_mcp.md) | MultiServerMCPClient & FastMCP | Cách kết nối Agent với các công cụ bên ngoài theo chuẩn Model Context Protocol. |
| [09_skills.md](../guideline/09_skills.md) | Đóng gói kỹ năng tái sử dụng | Chuẩn cấu trúc file `SKILL.md` để Agent nạp kỹ năng động. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Xây dựng giao diện Streaming v3 hiển thị trực tiếp ra Terminal

Tạo file `src/streaming_cli.py` sử dụng chuẩn `version="v3"` của LangChain:

```python
"""Client giao diện CLI thời gian thực sử dụng Streaming v3 Typed Projections."""

import sys
import asyncio
from src.agent_planner import build_planning_agent


async def run_streaming_cli(task: str):
    """Lắng nghe và hiển thị các stream văn bản và tool calls thời gian thực."""
    agent = build_planning_agent()
    
    print(f"\n[BẮT ĐẦU STREAMING TÁC VỤ]: {task}\n")
    print("=" * 60)
    
    # Kích hoạt streaming với version='v3'
    # Lưu ý: Với workflow bất đồng bộ, sử dụng astream_events
    stream = agent.astream_events(
        {"messages": [{"role": "user", "content": task}]},
        version="v3"
    )
    
    async for event in stream:
        event_type = event.get("event")
        
        # 1. Stream token nội dung suy nghĩ / trả lời
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and chunk.content:
                # In trực tiếp token ra console không đệm dòng
                sys.stdout.write(chunk.content)
                sys.stdout.flush()
                
        # 2. Stream thông báo khi Agent chuẩn bị gọi Tool
        elif event_type == "on_tool_start":
            tool_name = event.get("name")
            tool_input = event.get("data", {}).get("input")
            print(f"\n\n🛠️  [TOOL START]: Calling `{tool_name}` with args: {tool_input}")
            
        # 3. Stream khi Tool hoàn thành và trả về kết quả
        elif event_type == "on_tool_end":
            tool_name = event.get("name")
            output_snippet = str(event.get("data", {}).get("output"))[:120]
            print(f"✅ [TOOL DONE]: `{tool_name}` completed. Output preview: {output_snippet}...\n")
            
    print("\n" + "=" * 60)
    print("🎉 TÁC VỤ STREAMING HOÀN TẤT!")


if __name__ == "__main__":
    test_task = "Khảo sát workspace và viết một hàm tính giai thừa vào file src/math_service.py"
    asyncio.run(run_streaming_cli(test_task))
```

### Bước 2: Tích hợp Trí nhớ dài hạn cá nhân hóa (Personalized Memory)

Tạo file `src/memory_config.py` để ghi nhớ thói quen của từng developer:

```python
"""Quản lý trí nhớ dài hạn phân vùng theo User ID."""

from langgraph.store.memory import InMemoryStore
from deepagents.middleware.memory import MemoryMiddleware


def get_personalized_memory_middleware():
    """Khởi tạo MemoryMiddleware với InMemoryStore (hoặc SeekDB/Redis trong production)."""
    # Store lưu trữ các key-value pairs độc lập với session
    store = InMemoryStore()
    
    # Cấu hình middleware lưu trữ theo namespace của từng user
    memory_middleware = MemoryMiddleware(
        store=store,
        # Tự động nạp memory tương ứng với user_id được truyền trong cấu hình
        namespace_factory=lambda config: ("users", config.get("configurable", {}).get("user_id", "default_dev")),
    )
    return memory_middleware
```

### Bước 3: Kết nối công cụ bên ngoài qua chuẩn Model Context Protocol (MCP)

Tạo file `src/mcp_integration.py` minh họa cách kết nối một MCP Server vào Deep Agent:

```python
"""Tích hợp công cụ ngoại vi qua MultiServerMCPClient."""

from langchain_mcp import MultiServerMCPClient


async def get_mcp_tools():
    """Khởi tạo client MCP và lấy danh sách tools từ các máy chủ ngoại vi."""
    # Khai báo các MCP server cần kết nối (ví dụ: GitHub MCP, Postgres MCP hoặc local server)
    client = MultiServerMCPClient(
        servers={
            "github_mcp": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_pat_here"},
            },
            # Bạn cũng có thể kết nối qua Streamable HTTP
            # "remote_mcp": {
            #     "transport": "http",
            #     "url": "http://localhost:8000/mcp",
            # }
        },
        tool_name_prefix=True,  # Đổi tên thành github_mcp__create_issue để chống xung đột tên
    )
    
    # Nạp toàn bộ danh sách tools bất đồng bộ
    mcp_tools = await client.get_tools()
    return mcp_tools
```

### Bước 4: Lắp ráp kiến trúc Coding Agent hoàn chỉnh (9 Phases)

Tạo file `src/agent_production.py` kết hợp toàn bộ thành quả từ Phase 1 đến Phase 8:

```python
"""Production Coding Agent: Đầy đủ VFS, Planning, Execution, Subagents, Safety, Quality Gate, Memory và Streaming."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.middleware.todo import TodoListMiddleware

from src.backend import get_workspace_backend
from src.security_config import get_secure_whitelist_permissions
from src.memory_config import get_personalized_memory_middleware
from src.tools.test_runner import run_pytest

load_dotenv()


def build_production_agent():
    # Model cấu hình qua AgentSeek / LLM Gateway
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")
    permissions = get_secure_whitelist_permissions()
    memory_middleware = get_personalized_memory_middleware()
    todo_middleware = TodoListMiddleware()

    production_prompt = """Bạn là một Senior Principal Software Engineer và Production AI Coding Agent.
Bạn có đầy đủ năng lực:
- Lập kế hoạch phân rã công việc chi tiết bằng `write_todos`.
- Tự động định vị, phẫu thuật mã nguồn an toàn bằng Virtual File System.
- Thực thi kiểm thử và bảo đảm chất lượng nghiêm ngặt trước khi báo cáo.
- Ghi nhớ thói quen, phong cách lập trình của từng kỹ sư để tối ưu hóa sự phối hợp.
Luôn tuân thủ tuyệt đối các quy tắc an toàn bảo mật và không tiết lộ bí mật hệ thống.
"""

    agent = create_deep_agent(
        model=llm,
        tools=[run_pytest],
        backend=backend,
        permissions=permissions,
        middleware=[todo_middleware, memory_middleware],
        system_prompt=production_prompt,
    )
    return agent
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm giao diện Streaming với đầy đủ các middleware bảo vệ:

```bash
python -m src.streaming_cli
```

**Trải nghiệm của Developer**:
1. Terminal phản hồi ngay lập tức: Từng từ suy nghĩ của Agent tuôn ra theo thời gian thực.
2. Khi Agent quyết định lập kế hoạch, terminal hiển thị khối màu xanh:
   `🛠️  [TOOL START]: Calling write_todos...`
3. Tiếp theo là các sự kiện đọc file, sửa file và chạy unit test hiển thị tuần tự, minh bạch.
4. Mọi sở thích code của bạn (ví dụ: dùng type hints dạng `list[str]` thay vì `List[str]`) được lưu vào memory cá nhân và tự động áp dụng trong các lần gọi tiếp theo!

---

## 5. Checkpoint — Tự kiểm tra

- [ ] Script `streaming_cli.py` hiển thị token gõ chữ mượt mà, không bị hiện tượng chờ toàn bộ tin nhắn mới in ra.
- [ ] Các thông báo `on_tool_start` và `on_tool_end` hiển thị đúng lúc tool đang chạy.
- [ ] Hệ thống phân biệt được ngữ cảnh khi bạn truyền các `user_id` khác nhau trong cấu hình `configurable`.
- [ ] Chạy `agentseek doctor` và xác nhận toàn bộ hệ thống đã sẵn sàng để deploy lên môi trường Staging/Production.

---

## 6. Lộ trình phát triển tiếp theo (Next Steps)

Chúc mừng bạn đã hoàn thành trọn vẹn cả 9 phases xây dựng một Coding Agent từ con số 0 đến cấp độ sản xuất!
Dưới đây là các hướng mở rộng nâng cao bạn có thể tiếp tục khám phá:
1. **Frontend Rich UI với CopilotKit**: Kết nối Agent vừa xây dựng với template `deepagents/streaming` hoặc `langchain/markdown-messages` của AgentSeek để có giao diện Web chat tuyệt đẹp kèm trình soạn thảo code song song.
2. **Triển khai Cloud với `mda` CLI**: Khám phá Managed Deep Agents trên LangSmith để đưa Agent lên Cloud chỉ với một dòng lệnh `mda deploy`.
3. **Mở rộng kho MCP**: Tích hợp các MCP server như Docker MCP, Sentry MCP để biến Agent thành kỹ sư DevOps tự động theo dõi lỗi runtime và sửa bug tự động trên production.
