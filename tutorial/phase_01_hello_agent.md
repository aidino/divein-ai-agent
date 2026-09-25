# Phase 1: Hello Coding Agent — Khung sườn với AgentSeek
> **Prerequisite**: Không có
> **Thời gian ước tính**: 1-2 giờ  
> **AgentSeek template tham khảo**: `deepagents/default`
> **Bạn sẽ học**: Vòng đời AgentSeek, kiến trúc 3 tầng của Agent, Context Engineering, và cách khởi tạo một Deep Agent cơ bản.

## Mục tiêu
Hiểu được kiến trúc tổng thể của một coding agent, cách sử dụng AgentSeek để khởi tạo và quản lý dự án, đồng thời nắm bắt ý tưởng Context Engineering trong thiết kế hệ thống.

## Concept chính

### Kiến trúc 3 tầng (3-layer architecture)
Phát triển Agent hiện đại được chia thành 3 tầng từ dưới lên:
- **Tầng Runtime (LangGraph)**: Cung cấp execution engine, đảm bảo bền vững (durable execution), streaming, và lưu trữ state (persistence).
- **Tầng Framework (LangChain)**: Cung cấp model abstraction, tool interface, và các chuẩn mực giao tiếp.
- **Tầng Harness (Deep Agents)**: Cung cấp bộ công cụ "mở hộp là dùng được" (out-of-the-box) như hệ thống file ảo, lập kế hoạch task, và long-term memory. Với một coding agent, tầng Harness giúp nó có sẵn năng lực đọc/ghi mã nguồn mà không cần tự xây dựng từ đầu.

### Context Engineering
Thay vì nhồi nhét toàn bộ mã nguồn vào prompt (prompt stuffing) khiến LLM bị tràn context, mất tập trung và tốn chi phí, Deep Agents sử dụng Context Engineering. LLM được cung cấp một hệ thống tập tin ảo (Virtual File System) để chủ động đọc, ghi, và tìm kiếm mã nguồn theo nhu cầu. Điều này giúp Agent phân bổ sự chú ý chính xác vào phần code cần sửa, giống như cách một lập trình viên con người làm việc.

### Vòng đời AgentSeek
AgentSeek là công cụ quản lý dự án AI chuẩn mực, giúp bạn không phải tự cấu hình môi trường phức tạp:
- `create`: Sinh dự án từ template có sẵn.
- `info`: Xem thông tin tổng quan của dự án.
- `task`: Chạy các script chuẩn bị môi trường (như cài dependencies).
- `doctor`: Kiểm tra các điều kiện hệ thống trước khi chạy.
- `dev`: Khởi chạy backend và frontend để phát triển.

### Khởi tạo Deep Agent và Custom Tools
API `create_deep_agent()` là trái tim của ứng dụng. Bạn chỉ cần cung cấp `model`, `tools` và `system_prompt`. Bất kỳ hàm Python nào có đủ Type Annotation (kiểu dữ liệu), Docstring (mô tả công dụng) và Default values (giá trị mặc định) đều trở thành custom tool cho Agent, cho phép coding agent giao tiếp với các hệ thống ngoại vi (ví dụ: chạy linter, kiểm tra git status).

### Multi-provider và LangSmith
Dự án được cấu hình qua `.env` hỗ trợ nhiều nhà cung cấp mô hình như SiliconFlow, OpenAI, Anthropic, Google thông qua biến `AGENTSEEK_MODEL_PROVIDER` và `AGENTSEEK_MODEL`. Việc cấu hình LangSmith Tracing giúp bạn dễ dàng theo dõi, debug chuỗi suy luận của coding agent khi xử lý các task lập trình phức tạp.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | file:///home/lai/Documents/divein-ai-agent/guideline/00_preparation.md | Mục 1 đến 8 | Cách sử dụng vòng đời AgentSeek và cấu hình model provider qua `.env` |
| 2 | file:///home/lai/Documents/divein-ai-agent/guideline/03_agent_framework_to_agent_harness.md | Toàn bộ | Phân biệt LangGraph, LangChain, Deep Agents và triết lý Context Engineering |
| 3 | file:///home/lai/Documents/divein-ai-agent/guideline/04_quickstart_first_deep_agent.md | Tham số của `create_deep_agent` và viết custom tool | Cách code một Agent cơ bản với công cụ tự tạo |
| 4 | file:///home/lai/Documents/divein-ai-agent/guideline/01_deepagent_version_update.md | Các thay đổi ở v0.7 (Prompt, Todo) | Hiểu lý do tại sao system prompt trống và Todo phải bật thủ công trong phiên bản mới |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Khởi tạo dự án bằng AgentSeek
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/00_preparation.md
**Làm gì**: Sử dụng `agentseek create` với template `deepagents/default` để tạo dự án mới, sau đó chạy `agentseek task` và `agentseek doctor` để chuẩn bị môi trường.
**Tại sao**: Template này cung cấp khung sườn hoàn chỉnh cho một dự án Deep Agents, giúp bạn có ngay cấu trúc thư mục chuẩn và các công cụ quản lý vòng đời.

### Bước 2: Cấu hình Model Provider và LangSmith
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/00_preparation.md
**Làm gì**: Thiết lập các biến môi trường `AGENTSEEK_MODEL_PROVIDER`, `AGENTSEEK_MODEL` cùng với API key trong file `.env`. Kích hoạt `LANGSMITH_TRACING` để thu thập dữ liệu debug.
**Tại sao**: Coding agent cần một LLM đủ thông minh để phân tích logic code, và LangSmith là bắt buộc để theo dõi tại sao agent lại quyết định sửa file bị lỗi.

### Bước 3: Định nghĩa Custom Tool đầu tiên
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/04_quickstart_first_deep_agent.md
**Làm gì**: Viết một tool Python đơn giản với đầy đủ type hint, docstring và giá trị mặc định.
**Tại sao**: Coding agent không chỉ đọc viết text, nó cần thực thi lệnh, format code, hoặc linting. Các custom tools này giúp mở rộng năng lực của agent.

### Bước 4: Khởi tạo Agent với create_deep_agent()
**Đọc**: file:///home/lai/Documents/divein-ai-agent/guideline/04_quickstart_first_deep_agent.md và file:///home/lai/Documents/divein-ai-agent/guideline/01_deepagent_version_update.md
**Làm gì**: Viết system prompt định hình vai trò của coding agent, sau đó truyền model, system prompt và tools vào API `create_deep_agent()`.
**Tại sao**: Đây là bước lắp ráp cuối cùng, kết nối LLM với các công cụ thành một thực thể tự chủ có khả năng giải quyết bài toán lập trình.

## ✅ Checkpoint — Tự kiểm tra
- Bạn có thể chạy `agentseek dev` và tương tác với Agent không?
- Khi bạn yêu cầu Agent sử dụng tool, bạn có thấy nó tự động gọi hàm custom tool và trả về kết quả không?
- Bạn có thấy chuỗi suy luận (Trace) xuất hiện đầy đủ trong dashboard của LangSmith không?

## ⚠️ Lưu ý quan trọng
- **Đừng viết System Prompt quá dài**: Ở v0.7, framework đã bỏ các prompt hướng dẫn dài dòng. Hãy viết system prompt tập trung vào nghiệp vụ code của bạn.
- **Type Annotations là bắt buộc**: Nếu custom tool thiếu type hints hoặc docstring, LLM sẽ không biết cách gọi đúng tham số.

## 🔗 Tham khảo thêm
- AgentSeek template: `deepagents/default`
</Phase 1: Hello Coding Agent — Khung sườn với AgentSeek>
