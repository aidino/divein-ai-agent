# DiveIn AI Agent 🤖

Dự án học tập, nghiên cứu và thực hành chuyên sâu về **AI Coding Agent** sử dụng framework **Deep Agents** (hệ sinh thái LangChain / LangGraph) kết hợp cùng bộ công cụ vòng đời **AgentSeek**.

---

## 📂 Cấu trúc Repository

Repository được tổ chức thành 2 khu vực nội dung chính:

### 1. 📚 [deepagents-guideline/](deepagents-guideline/) — Giáo trình lý thuyết Deep Agents
Tập hợp toàn bộ 18 bài giảng chi tiết về framework Deep Agents:
- **Nền tảng & Kiến trúc**: Tổng quan 3 tầng (Runtime, Framework, Harness), Context Engineering, Virtual File System (VFS).
- **Kỹ thuật cốt lõi**: Task Planning (`TodoListMiddleware`), Quản lý ngữ cảnh & Auto-eviction, Đa đặc vụ (Subagents, Async Subagents, Dynamic Subagents với QuickJS).
- **Hạ tầng & Bảo mật**: Phân quyền hệ thống tập tin (`FilesystemPermission`), Sandbox cách ly mã nguồn, Human-in-the-Loop, Cổng kiểm soát chất lượng (`RubricMiddleware`).
- **Nâng cao & Production**: Giao thức Model Context Protocol (MCP), Event Streaming v3 GA, Trí nhớ dài hạn cá nhân hóa (v0.8 Personalized Memory), Kỹ năng (Skills).

### 2. 🛠️ [build-coding-agent-tutorial/](build-coding-agent-tutorial/) — Bộ Tutorial xây dựng Coding Agent
Bộ hướng dẫn thực hành 9 phases hoàn chỉnh, đưa bạn qua từng bước tự xây dựng một Coding Agent từ con số 0 đến cấp độ sản xuất:

| Phase | Tài liệu | Nội dung trọng tâm |
| :---: | :--- | :--- |
| **0** | [Báo cáo thiết kế V2](build-coding-agent-tutorial/00_design_report.md) | Tổng quan kiến trúc hệ thống Coding Agent 9 tầng. |
| **1** | [Hello Coding Agent](build-coding-agent-tutorial/phase_01_hello_agent.md) | Khởi tạo dự án với AgentSeek, cấu hình model provider, custom tool AST, LangSmith tracing. |
| **2** | [File Operations](build-coding-agent-tutorial/phase_02_file_operations.md) | 7 built-in VFS tools, `FilesystemBackend(virtual_mode=True)`, quy trình `glob` -> `grep` -> `read` -> `edit`. |
| **2.5** | [Codebase Intelligence](build-coding-agent-tutorial/phase_025_codebase_intelligence.md) | Điều hướng codebase lớn bằng AST Repo Map, GraphRAG (LightRAG) và tích hợp Understand-Anything. |
| **3** | [Task Planning](build-coding-agent-tutorial/phase_03_task_planning.md) | Phân rã công việc với `TodoListMiddleware`, Cognitive Anchor chống mất phương hướng khi nén context. |
| **4** | [Code Execution](build-coding-agent-tutorial/phase_04_code_execution.md) | Chạy code an toàn với 3 mô hình Sandbox (Local, Docker AIO, Cloud MicroVM), chu trình TDD tự động. |
| **5** | [Sub-agents](build-coding-agent-tutorial/phase_05_subagents.md) | Phân chia chuyên môn theo mô hình Coordinator -> Researcher -> Coder -> Tester, cách ly ngữ cảnh. |
| **6** | [Safety & Permissions](build-coding-agent-tutorial/phase_06_safety.md) | Kiểm soát quyền truy cập file, quy tắc First-Match-Wins, Whitelist 4 tầng và Human-in-the-Loop. |
| **7** | [Quality Gate](build-coding-agent-tutorial/phase_07_quality_gate.md) | Nghiệm thu tự động với `RubricMiddleware`, Evidence Tool thu thập bằng chứng pytest, nguyên tắc Fail-Closed. |
| **8** | [Production Polish](build-coding-agent-tutorial/phase_08_production.md) | Event Streaming v3 GA, Trí nhớ cá nhân hóa theo developer, tích hợp MCP và dịch vụ Managed Deep Agents. |

Xem chi tiết hướng dẫn bắt đầu tại: [**build-coding-agent-tutorial/README.md**](build-coding-agent-tutorial/README.md).