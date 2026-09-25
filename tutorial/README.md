# 🤖 Coding Agent Tutorial — Xây dựng Coding Agent với Deep Agents + AgentSeek

> Bộ tutorial 9 phase hướng dẫn bạn tự xây dựng một coding agent hoàn chỉnh,
> ứng dụng kiến thức từ khóa học Deep Agents (LangChain ecosystem).
>
> **Format**: Concept-only — chỉ giải thích concept + chỉ đến tài liệu, bạn tự code hoàn toàn.

## Yêu cầu

- Python 3.12+, uv, Node.js LTS
- AgentSeek (`uv tool install --upgrade agentseek`)
- API key: SiliconFlow / OpenAI / Anthropic / Google
- Đã hoàn thành khóa học Deep Agents (`guideline/`)

## Lộ trình

| Phase | File | Mục tiêu | AgentSeek Template | Thời gian |
|-------|------|----------|-------------------|-----------|
| 1 | [Hello Agent](phase_01_hello_agent.md) | Scaffold + `create_deep_agent()` | `deepagents/default` | 1-2h |
| 2 | [File Operations](phase_02_file_operations.md) | 7 file tools + VFS | — | 2-3h |
| 2.5 | [Codebase Intelligence](phase_025_codebase_intelligence.md) | AST + GraphRAG (LightRAG) | `deepagents/powercontext` | 3-4h |
| 3 | [Task Planning](phase_03_task_planning.md) | TodoListMiddleware + Summarization | — | 1-2h |
| 4 | [Code Execution](phase_04_code_execution.md) | 3 Sandbox options | `deepagents/sandbox` | 2-3h |
| 5 | [Sub-agents](phase_05_subagents.md) | Researcher → Coder → Tester | `deepagents/subagents-dynamic` | 2-3h |
| 6 | [Safety](phase_06_safety.md) | Permissions + HITL | — | 2h |
| 7 | [Quality Gate](phase_07_quality_gate.md) | RubricMiddleware + evidence | `langchain/rubric` | 2-3h |
| 8 | [Production](phase_08_production.md) | Streaming v3 + Memory + MCP + H2/2026 | `deepagents/streaming` | 3-4h |

**Tổng thời gian ước tính**: ~19-27 giờ

## Cách sử dụng

1. Đọc [Design Report V2](../guideline/) để hiểu tổng quan kiến trúc
2. Làm từng Phase **theo thứ tự** — mỗi phase xây thêm một subsystem
3. **Đọc tài liệu** theo bảng chỉ dẫn trong từng phase **trước khi code**
4. Tham khảo AgentSeek template khi cần xem cấu trúc chuẩn
5. Tự viết code — tutorial chỉ giải thích concept, không cung cấp code

## AgentSeek Quick Start

```bash
# Liệt kê templates
agentseek create --list-templates --checkout main

# Tạo project từ template
agentseek create deepagents/default --checkout main

# Lifecycle commands
agentseek info          # Xem project info
agentseek task --list   # Xem tasks
agentseek task sync     # Cài Python deps
agentseek task frontend # Cài frontend deps
agentseek doctor        # Kiểm tra môi trường
agentseek dev           # Chạy dev server
```
