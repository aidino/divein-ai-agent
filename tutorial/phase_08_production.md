# Phase 8: Production Polish — Streaming, Memory, MCP, và H2/2026 Stack
> **Prerequisite**: Phase 7
> **Thời gian ước tính**: 3-4 giờ  
> **AgentSeek template tham khảo**: `deepagents/streaming`, `deepagents/mcp`, `deepagents/powercontext`
> **Bạn sẽ học**: Streaming v3 GA, interleave(), MemoryMiddleware & StoreBackend, Context namespace, MCP client/primitives, Skills module, H2/2026 Managed Production Stack.

## Mục tiêu
Lắp ghép tất cả các tính năng nâng cao để biến Agent từ một prototype thành một ứng dụng thương mại hoàn chỉnh (Production-ready): stream dữ liệu mượt mà cho UI, ghi nhớ dài hạn, tích hợp công cụ qua chuẩn MCP, đóng gói kỹ năng, và kiến trúc deploy trên mây (H2/2026 Stack).

## Concept chính

### 1. Streaming (v3 GA) & Content-block Protocol
Luồng dữ liệu thời gian thực là điều kiện tiên quyết cho UX mượt mà. 
- API `stream_events(version='v3')` hỗ trợ typed projections, trả về sự kiện rõ ràng (`stream.messages`, `stream.tool_calls`, `stream.subagents`).
- Quản lý Subagent bằng handle (name, unique path, status lifecycle).
- Hàm `interleave()` giúp sắp xếp, ghép các sự kiện luồng cho đúng thứ tự.
- Giao thức tập trung vào Content-block: phân biệt rõ `text`, `reasoning` (chuỗi suy luận), `tool_call` và `image`.

### 2. Long-term Memory & Personalization
Agent cần khả năng nhớ sở thích và quá khứ giao tiếp.
- `MemoryMiddleware` cùng `StoreBackend` (hoặc `CompositeBackend`) quản lý trí nhớ dài hạn.
- Cơ chế cá nhân hóa (Personalized memory v0.8) cho phép lưu trữ theo từng người dùng đã xác thực (per-authenticated-caller) qua namespace partitioning.
- `PowerContext` cung cấp cơ chế handoff (chuyển giao bối cảnh) giữa các agent mà không bị rớt dữ liệu (thường đi kèm với seekdb).

### 3. Model Context Protocol (MCP) Integration
Kết nối agent với hệ sinh thái lập trình.
- Cấu trúc 3 thành phần: Tools (Công cụ), Resources (Tài nguyên tĩnh), Prompts (Kịch bản).
- `MultiServerMCPClient` kết nối qua 2 loại giao thức: `stdio` hoặc `http transport`.
- Sử dụng `tool_name_prefix=True` để tránh xung đột tên gọi. Bắt buộc gọi qua `ainvoke` (Async-only requirement).
- Giúp agent tương tác với GitHub, LSP (Language Server Protocol), CI/CD một cách chuẩn hóa.

### 4. Gói Kỹ Năng (Skills)
- Kỹ thuật đóng gói Tool, Prompt, và Resources thành một module tái sử dụng (`SKILL.md`).
- Context Hub (trên LangSmith): Giúp quản lý phiên bản (version-controlled) cho các kỹ năng và hướng dẫn này.

### 5. Kiến trúc H2/2026 Production Stack
Tổng quan các công cụ triển khai hiện đại:
- **Managed Deep Agents (Public Beta)**: Triển khai serverless qua CLI `mda` và hosted runtime.
- **LLM Gateway**: Trạm điều phối model, tự động fallback khi lỗi mạng, giới hạn request (rate limiting), che giấu thông tin nhạy cảm (PII redaction), quản lý chi phí (spend caps).
- **LangSmith Sandboxes GA**: Công nghệ microVM cung cấp môi trường thực thi code an toàn với tính năng snapshots/forks siêu tốc.

### 6. Kiến trúc Tổng quan (Final Review)
Hợp nhất tất cả các phase (từ cơ bản, phân quyền, TDD rubric, đến MCP và Memory) thành một quy trình chuẩn duy nhất cho dự án lớn.

## 📖 Đọc tài liệu

Bảng chỉ dẫn đọc — đọc theo thứ tự trước khi code:

| # | Tài liệu | Phần cần đọc | Bạn sẽ hiểu được gì |
|---|----------|-------------|---------------------|
| 1 | [16_streaming.md](file:///home/lai/Documents/divein-ai-agent/guideline/16_streaming.md) | V3 Streaming & Interleave | Cách push dữ liệu thời gian thực cho Client. |
| 2 | [10_long_term_memory.md](file:///home/lai/Documents/divein-ai-agent/guideline/10_long_term_memory.md) | MemoryMiddleware | Cách lưu trữ ngữ cảnh cross-session theo namespace. |
| 3 | [14_mcp.md](file:///home/lai/Documents/divein-ai-agent/guideline/14_mcp.md) | MCP Client & Transport | Tích hợp công cụ ngoại vi với MCP. |
| 4 | [09_skills.md](file:///home/lai/Documents/divein-ai-agent/guideline/09_skills.md) | Kỹ năng và đóng gói | Cấu trúc SKILL.md và cách nạp động. |

## 🧭 Hướng dẫn thực hiện

### Bước 1: Nâng cấp luồng Streaming v3
**Đọc**: [16_streaming.md](file:///home/lai/Documents/divein-ai-agent/guideline/16_streaming.md)
**Làm gì**: Sử dụng `stream_events(version='v3')` và cấu hình UI frontend để xử lý các chunks `text`, `reasoning` và `tool_calls` tách biệt. Kết hợp `interleave()` nếu xử lý đa subagent.
**Tại sao**: Cho phép người dùng thấy agent đang "suy nghĩ" và "hành động" thay vì chờ mỏi mòn 30s mới thấy kết quả trả về một cục.

### Bước 2: Tích hợp Bộ nhớ dài hạn (Long-Term Memory)
**Đọc**: [10_long_term_memory.md](file:///home/lai/Documents/divein-ai-agent/guideline/10_long_term_memory.md)
**Làm gì**: Thêm `MemoryMiddleware`, khởi tạo `StoreBackend` và chia nhỏ không gian lưu trữ (`namespace`) bằng user ID để agent ghi nhớ config cá nhân hóa.
**Tại sao**: Giúp trải nghiệm liền mạch, agent nhận biết lịch sử thay vì phải bị hướng dẫn lại từ đầu mỗi session.

### Bước 3: Cắm Tools bằng MCP Protocol
**Đọc**: [14_mcp.md](file:///home/lai/Documents/divein-ai-agent/guideline/14_mcp.md)
**Làm gì**: Khởi tạo `MultiServerMCPClient`, khai báo một server qua `stdio` (vd: `npx github-mcp-server`), dùng `tool_name_prefix=True`, và bind vào agent với các hàm async.
**Tại sao**: Thay vì tự viết code tương tác Github API, MCP cung cấp mọi tools chuẩn mà cộng đồng đã xây dựng.

## ✅ Checkpoint — Tự kiểm tra
- Frontend nhận được streaming theo chunk từ agent, bao gồm cả nội dung "reasoning".
- Đóng session, mở session mới, agent vẫn nhớ được tên hoặc cấu hình bạn đã set.
- Agent có khả năng gọi tool ngoài thông qua MCP chuẩn và không bị crash luồng bất đồng bộ.

## ⚠️ Lưu ý quan trọng
- Luôn phải đảm bảo `ainvoke` (bất đồng bộ) khi làm việc với MCP.
- Việc lưu memory dài hạn cần chú ý rủi ro Privacy Data (PII), kết hợp với LLM Gateway để làm sạch dữ liệu.
- Theo dõi cẩn thận memory footprint khi dùng MemoryMiddleware.

## 🔗 Tham khảo thêm
- Các AgentSeek templates: `deepagents/streaming`, `deepagents/mcp`, `deepagents/powercontext`.
- Theo dõi docs của LangSmith Sandboxes khi đưa sản phẩm ra Production.
