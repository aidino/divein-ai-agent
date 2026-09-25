# Phase 2.5: Codebase Intelligence — Hiểu codebase lớn

> **Mục tiêu**: Xây dựng lớp "trí tuệ điều hướng mã nguồn" (Codebase Intelligence) cho Agent, giúp nó hiểu kiến trúc, đồ thị phụ thuộc và ngữ nghĩa của các dự án lớn hàng trăm nghìn dòng code bằng kỹ thuật AST (Tree-sitter), GraphRAG (LightRAG), và tích hợp tùy chọn [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything).
>
> **Thời gian ước tính**: 2.5 - 3.5 giờ
>
> **AgentSeek template tham khảo**: `deepagents/powercontext`
>
> **Prerequisites**: Hoàn thành [Phase 2: File Operations](phase_02_file_operations.md).

---

## 1. Tổng quan & Lý thuyết cốt lõi

### 1.1 Vấn đề khi Agent đối mặt với Codebase quy mô lớn
Trong Phase 2, bạn đã thấy Agent dùng `grep` và `glob` để tìm code. Phương pháp này hoạt động tốt với các dự án nhỏ (dưới 50 file). Nhưng khi đối mặt với một repository thực tế (hàng nghìn file code), Agent sẽ gặp các bế tắc:

1. **Token Explosion**: Một lệnh `grep "User"` có thể trả về 1.000 kết quả từ hàng trăm file, làm tràn toàn bộ context window hoặc kích hoạt auto-eviction liên tục.
2. **Thiếu hiểu biết ngữ nghĩa (Semantic Blindness)**: Người dùng hỏi: *"Đoạn code nào xử lý việc hoàn tiền khi thanh toán thất bại?"*, nhưng code lại đặt tên hàm là `revert_transaction()` hoặc `process_chargeback()`. Tìm kiếm từ khóa thuần túy sẽ hoàn toàn thất bại.
3. **Mù quan hệ phụ thuộc (No Dependency / Call Graph)**: LLM không biết nếu sửa hàm `get_user_profile()` thì có bao nhiêu service khác đang gọi nó và sẽ bị ảnh hưởng (Breaking Changes).

### 1.2 Phương pháp tiếp cận 3 tầng (3-Tier Navigation Architecture)

```
┌────────────────────────────────────────────────────────┐
│               Tầng 3: Agentic Reasoning                │
│    Agent tự quyết định chiến lược tìm kiếm theo nhu cầu │
├──────────────────────────┬─────────────────────────────┤
│  Tầng 1: Deterministic   │      Tầng 2: Semantic       │
│  - AST Indexing          │  - GraphRAG (LightRAG)      │
│  - Repo Map (Tree-sitter)│  - Entity-Relationship Graph│
│  - Call Graph & Symbols  │  - Dual-level retrieval     │
├──────────────────────────┴─────────────────────────────┤
│                  Thực thi & Kiểm chứng                 │
│         Built-in grep | read_file | edit_file          │
└────────────────────────────────────────────────────────┘
```

1. **Tầng Xác định (Deterministic - AST & Symbol Table)**:
   - Sử dụng trình phân tích cú pháp (như Python `ast` hoặc `Tree-sitter`) để bóc tách cấu trúc code: tên file, tên class, chữ ký hàm (function signatures), docstring tóm tắt.
   - Tạo ra một **Repo Map** siêu gọn: chỉ chứa khung sườn của codebase mà không chứa phần thân hàm (function body). Điều này giúp nhét toàn bộ bản đồ kiến trúc của một dự án 10.000 dòng code chỉ trong khoảng 1.000 - 2.000 tokens!

2. **Tầng Ngữ nghĩa (Semantic - GraphRAG với LightRAG)**:
   - Thay vì RAG truyền thống (cắt nhỏ code thành các đoạn text rời rạc rồi nhúng vector), **LightRAG** trích xuất các Thực thể (Entities: Class, Function, API Endpoint) và Mối quan hệ (Relationships: `calls`, `inherits`, `imports`, `depends_on`).
   - Xây dựng một đồ thị tri thức 2 tầng (**Dual-Level Retrieval**):
     - *Low-Level*: Truy vấn chi tiết một hàm cụ thể và các tham số của nó.
     - *High-Level*: Truy vấn toàn cục về luồng nghiệp vụ ("Kiến trúc module auth hoạt động ra sao?").
   - Hỗ trợ **Incremental Update**: Khi một file code thay đổi, chỉ cập nhật node đó trên đồ thị mà không cần re-index toàn bộ dự án.

3. **Tầng Tự chủ (Agentic)**:
   - Cung cấp cho Agent các công cụ để tự lựa chọn: Khi cần tìm hiểu kiến trúc -> dùng Repo Map hoặc Semantic Search; khi đã biết chính xác file và biến -> dùng `grep` và `read_file`.

---

## 2. Tài liệu tham khảo mở rộng

| Tài liệu | Phần trọng tâm | Mục tiêu học tập |
| :--- | :--- | :--- |
| [05_virtual_filesystem.md](../guideline/05_virtual_filesystem.md) | Giới hạn của grep và glob | Hiểu tại sao các công cụ duyệt text thuần túy không đáp ứng được dự án lớn. |
| [14_mcp.md](../guideline/14_mcp.md) | Kiến trúc MCP & FastMCP | Cách gói các công cụ phân tích code thông minh thành MCP server để cắm vào Agent. |
| [LightRAG GitHub](https://github.com/HKUDS/LightRAG) | Architecture & Query Modes | Nghiên cứu mô hình đồ thị tri thức 2 tầng và 5 query modes (naive, local, global, hybrid, mix). |
| [Understand-Anything GitHub](https://github.com/Egonex-AI/Understand-Anything) | Multi-Agent Pipeline & MCP Skills | Tìm hiểu cách xây dựng đồ thị tương tác và dashboard trực quan hóa codebase. |

---

## 3. Hướng dẫn thực hành từng bước

### Bước 1: Xây dựng công cụ tạo Repo Map bằng AST

Chúng ta sẽ tạo một tool `generate_repo_map` sử dụng thư viện `ast` chuẩn của Python để quét toàn bộ workspace và tạo ra bản tóm tắt cấu trúc cực kỳ tiết kiệm token.

Tạo file `src/tools/repo_mapper.py`:

```python
"""Công cụ sinh Repo Map cấu trúc dự án bằng AST."""

import ast
import os
from langchain_core.tools import tool


def extract_symbols_from_code(code_content: str, filename: str) -> str:
    """Bóc tách chữ ký class và function từ code, bỏ qua phần body."""
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return f"- File: {filename} (Lỗi cú pháp, không thể phân tích AST)\n"

    lines = [f"File: {filename}"]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"  class {node.name}:")
            for sub_node in node.body:
                if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [arg.arg for arg in sub_node.args.args]
                    lines.append(f"    def {sub_node.name}({', '.join(args)}): ...")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            lines.append(f"  def {node.name}({', '.join(args)}): ...")

    return "\n".join(lines)


@tool
def generate_repo_map(workspace_dir: str = "workspace") -> str:
    """Tạo bản đồ cấu trúc mã nguồn (Repo Map) của toàn bộ các file Python trong workspace.
    
    Tool này quét cây thư mục, trích xuất tất cả tên Class, Method, Function và chữ ký tham số
    mà không tải nội dung chi tiết của hàm, giúp Agent nắm toàn cảnh kiến trúc với chi phí token tối thiểu.
    """
    repo_maps = []
    for root, _, files in os.walk(workspace_dir):
        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), workspace_dir)
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    symbols = extract_symbols_from_code(content, rel_path)
                    repo_maps.append(symbols)
                except Exception as e:
                    repo_maps.append(f"File: {rel_path} (Không thể đọc: {e})")

    if not repo_maps:
        return "Workspace không có file Python nào."

    header = "=== BẢN ĐỒ CẤU TRÚC CODEBASE (REPO MAP) ===\n"
    return header + "\n\n".join(repo_maps)
```

### Bước 2: Tích hợp công cụ Semantic Code Search (Mô hình hóa GraphRAG)

Khi tích hợp với thư viện đồ thị tri thức như LightRAG, bạn có thể triển khai dưới dạng một tool hoặc kết nối qua MCP client. Dưới đây là cách đóng gói công cụ truy vấn ngữ nghĩa hai tầng (Entity-Relationship Search):

Tạo file `src/tools/semantic_code_search.py`:

```python
"""Công cụ Semantic Search kết hợp Knowledge Graph cho Codebase."""

from langchain_core.tools import tool


@tool
def search_codebase_semantic(query: str, search_depth: str = "hybrid") -> str:
    """Tìm kiếm mã nguồn theo ngữ nghĩa và mối quan hệ giữa các module.
    
    Sử dụng công cụ này khi bạn muốn:
    - Tìm kiếm dựa trên khái niệm/nghiệp vụ (VD: 'hệ thống hoàn tiền', 'xác thực token jwt').
    - Tìm hiểu các hàm có liên quan hoặc phụ thuộc lẫn nhau.

    Args:
        query: Câu hỏi hoặc khái niệm cần tìm kiếm.
        search_depth: Chế độ tìm kiếm:
            - 'local': Tập trung vào chi tiết thực thể (hàm, class, tham số cụ thể).
            - 'global': Tập trung vào bức tranh tổng thể và luồng nghiệp vụ.
            - 'hybrid': Kết hợp cả hai để đưa ra ngữ cảnh đầy đủ nhất.
    """
    # Trong môi trường production, hàm này sẽ gọi LightRAG engine hoặc seekdb vector store.
    # Ở đây chúng ta mô phỏng kết quả trả về từ GraphRAG index:
    results = [
        f"=== KẾT QUẢ TÌM KIẾM NGỮ NGHĨA CHO: '{query}' (Mode: {search_depth}) ===",
        "1. Module liên quan: `src/services/payment_service.py`",
        "   - Hàm `revert_transaction(order_id, reason)`: Xử lý hoàn tiền giao dịch qua cổng thanh toán.",
        "   - Quan hệ: Được gọi bởi `src/controllers/order_controller.py:cancel_order()`.",
        "2. Module liên quan: `src/core/exceptions.py`",
        "   - Class `PaymentGatewayError`: Bắt ngoại lệ khi cổng thanh toán từ chối.",
    ]
    return "\n".join(results)
```

### Bước 3: Đào tạo chiến lược tìm kiếm phân tầng cho Agent

Tạo file `src/agent_intelligent.py` lắp ráp toàn bộ công cụ và hướng dẫn Agent tư duy theo 3 tầng:

```python
"""Agent tích hợp Codebase Intelligence."""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

from src.backend import get_workspace_backend
from src.tools.repo_mapper import generate_repo_map
from src.tools.semantic_code_search import search_codebase_semantic

load_dotenv()

INTELLIGENT_AGENT_PROMPT = """Bạn là một Senior Software Architect và Coding Agent cao cấp.

Bạn có các công cụ điều hướng codebase phân tầng:
1. TẦNG TỔNG QUAN (REPO MAP): Dùng `generate_repo_map` khi bắt đầu một dự án mới để nắm ngay danh sách tất cả class, method trong toàn bộ workspace mà không tốn nhiều token.
2. TẦNG NGỮ NGHĨA (SEMANTIC SEARCH): Dùng `search_codebase_semantic` khi câu hỏi của người dùng mang tính mô tả nghiệp vụ hoặc bạn chưa biết chính xác từ khóa trong code.
3. TẦNG CHI TIẾT (BUILT-IN TOOLS): Sau khi đã khoanh vùng được file và hàm mục tiêu:
   - Dùng `grep` để tìm chính xác dòng gọi hàm.
   - Dùng `read_file` để đọc chi tiết logic.
   - Dùng `edit_file` để thực hiện sửa đổi.

Tuyệt đối không đoán mò vị trí file. Hãy luôn bắt đầu từ Repo Map hoặc Semantic Search trước khi đọc sâu vào từng dòng code!
"""


def build_intelligent_agent():
    llm = ChatOpenAI(
        model=os.getenv("AGENTSEEK_MODEL", "zai-org/GLM-5.2"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
        temperature=0.0,
    )

    backend = get_workspace_backend("workspace")

    # Bổ sung các custom tools thông minh vào cùng 7 built-in file tools
    tools = [generate_repo_map, search_codebase_semantic]

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        backend=backend,
        system_prompt=INTELLIGENT_AGENT_PROMPT,
    )
    return agent


if __name__ == "__main__":
    bot = build_intelligent_agent()

    query = "Dự án này có những service nào và hàm nào chịu trách nhiệm hoàn tiền đơn hàng?"
    print(f"Câu hỏi: {query}\n")

    response = bot.invoke({"messages": [{"role": "user", "content": query}]})
    print("\n--- PHẢN HỒI TỪ AGENT ---")
    print(response["messages"][-1].content)
```

---

## 4. Kịch bản thực chiến (End-to-End Walkthrough)

Chạy thử nghiệm Agent thông minh:

```bash
python -m src.agent_intelligent
```

**Quan sát luồng xử lý**:
1. Agent nhận câu hỏi về "hệ thống hoàn tiền". Thay vì chạy hàng loạt lệnh `grep` vô định, Agent nhận thấy câu hỏi mang tính nghiệp vụ.
2. Agent gọi `generate_repo_map()` để nắm tổng thể cấu trúc các file trong thư mục `workspace/`.
3. Agent đồng thời gọi `search_codebase_semantic(query="hoàn tiền đơn hàng", search_depth="hybrid")`.
4. Nhờ kết quả từ đồ thị ngữ nghĩa, Agent lập tức biết hàm cần tìm là `revert_transaction()` nằm trong file `src/services/payment_service.py`.
5. Cuối cùng, Agent tổng hợp câu trả lời mạch lạc: liệt kê danh sách service từ Repo Map và giải thích chính xác luồng hoàn tiền.

---

## 5. Tùy chọn nâng cao: Tích hợp Understand-Anything

> **Dự án**: [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything)
> **Mức độ**: Advanced / Khuyến nghị cho dự án doanh nghiệp lớn

Nếu bạn muốn nâng cấp hệ thống thành một nền tảng phân tích mã nguồn cấp doanh nghiệp, bạn có thể tích hợp **Understand-Anything**:

### Ưu điểm vượt trội của Understand-Anything:
1. **Multi-Agent Analysis Pipeline**: Tự động sử dụng nhiều sub-agents chuyên biệt để quét dependencies, domain logic và kiến trúc hệ thống.
2. **Interactive Visual Dashboard**: Cung cấp giao diện Web trực quan (dạng đồ thị có thể zoom, pan, click) để developer con người và AI cùng quan sát cấu trúc code.
3. **Domain Mapping & Guided Tours**: Tự động sinh ra các lộ trình hướng dẫn (walkthrough tours) theo thứ tự phụ thuộc của code, giúp việc onboarding vào codebase phức tạp chỉ mất vài phút.
4. **Chuẩn hóa MCP**: Hỗ trợ xuất các chức năng thành các công cụ chuẩn Model Context Protocol (MCP) như `understand-chat`, `understand-explain`, `understand-diff`.

### Cách liên kết vào Deep Agents:
- **Cách 1: Pre-indexing**: Chạy CLI của Understand-Anything để tạo file `.ua/knowledge-graph.json`. Cho phép `FilesystemBackend` đọc thư mục `.ua/` để nạp đồ thị quan hệ vào Agent.
- **Cách 2: MCP Bridge**: Đăng ký Understand-Anything làm một MCP Server trong file cấu hình của AgentSeek, sau đó nạp các công cụ giải thích code vào Deep Agent thông qua `MultiServerMCPClient` (được hướng dẫn chi tiết ở Phase 8).

---

## 6. Checkpoint — Tự kiểm tra

- [ ] Tool `generate_repo_map` in ra chính xác danh sách class và hàm trong `workspace/` mà không bị lỗi syntax.
- [ ] Khi hỏi một câu hỏi nghiệp vụ trừu tượng, Agent biết ưu tiên gọi `generate_repo_map` hoặc `search_codebase_semantic` trước khi gọi `grep`.
- [ ] Token tiêu thụ trong trace của LangSmith giảm đáng kể so với việc đọc toàn bộ file bằng `read_file`.

---

## 7. Lỗi thường gặp & Best Practices

1. **Lỗi tràn RAM khi index thư mục rác**:
   - Luôn cấu hình bộ lọc loại trừ các thư mục: `.git/`, `__pycache__/`, `node_modules/`, `.venv/`, `.agentseek/`.
2. **Chi phí token khi lập chỉ mục GraphRAG**:
   - Việc sinh Knowledge Graph bằng LLM có tốn phí API một lần đầu. Hãy lưu cache đồ thị ra đĩa (dạng JSON hoặc SQLite / seekdb) và chỉ cập nhật các file có git diff thay đổi.
